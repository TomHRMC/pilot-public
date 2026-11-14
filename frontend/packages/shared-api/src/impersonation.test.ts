/**
 * impersonation store unit tests
 *
 * Location: packages/shared-api/src/impersonation.test.ts
 *
 * C-B15 Part B: Tests get/set/clear round-trip, invalid JSON → null,
 * custom event dispatched, useImpersonation reflects changes.
 *
 * NOTE: The shared-api vitest config uses environment: "node" (no jsdom).
 * We stub window + sessionStorage + CustomEvent for these tests. The
 * useImpersonation hook test requires React + jsdom, so it lives in the
 * web package test suite instead (see apps/web component tests).
 */

import { describe, it, expect, beforeEach, vi } from "vitest";

// ── Stub browser globals (node environment) ──────────────────────────────────

let store: Record<string, string> = {};

const sessionStorageStub = {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => {
    store[key] = value;
  },
  removeItem: (key: string) => {
    delete store[key];
  },
  clear: () => {
    store = {};
  },
};

const eventListeners: Record<string, Set<EventListener>> = {};

const windowStub = {
  sessionStorage: sessionStorageStub,
  dispatchEvent: (event: Event) => {
    const listeners = eventListeners[event.type] ?? new Set();
    listeners.forEach((fn) => fn(event));
    return true;
  },
  addEventListener: (type: string, listener: EventListener) => {
    if (!eventListeners[type]) eventListeners[type] = new Set();
    eventListeners[type].add(listener);
  },
  removeEventListener: (type: string, listener: EventListener) => {
    eventListeners[type]?.delete(listener);
  },
};

class CustomEventStub extends Event {
  detail: unknown;
  constructor(type: string, init?: { detail?: unknown }) {
    super(type);
    this.detail = init?.detail;
  }
}

// Assign stubs to global before importing the module
Object.defineProperty(globalThis, "window", {
  value: windowStub,
  writable: true,
  configurable: true,
});
Object.defineProperty(globalThis, "sessionStorage", {
  value: sessionStorageStub,
  writable: true,
  configurable: true,
});
Object.defineProperty(globalThis, "CustomEvent", {
  value: CustomEventStub,
  writable: true,
  configurable: true,
});

// Import after stubs are in place
import {
  getImpersonation,
  setImpersonation,
  clearImpersonation,
} from "./impersonation";

describe("impersonation store", () => {
  beforeEach(() => {
    store = {};
    // Clear event listeners
    for (const key of Object.keys(eventListeners)) {
      delete eventListeners[key];
    }
  });

  it("returns null when no session is stored", () => {
    expect(getImpersonation()).toBeNull();
  });

  it("set/get round-trip", () => {
    setImpersonation({ tenantId: "tenant-001", tenantName: "Acme Electric" });
    const session = getImpersonation();
    expect(session).toEqual({
      tenantId: "tenant-001",
      tenantName: "Acme Electric",
    });
  });

  it("clear removes the session", () => {
    setImpersonation({ tenantId: "tenant-001", tenantName: "Acme Electric" });
    expect(getImpersonation()).not.toBeNull();
    clearImpersonation();
    expect(getImpersonation()).toBeNull();
  });

  it("returns null for invalid JSON", () => {
    store["pilot.impersonation"] = "{invalid json";
    expect(getImpersonation()).toBeNull();
  });

  it("returns null for malformed object (missing fields)", () => {
    store["pilot.impersonation"] = JSON.stringify({ tenantId: "x" });
    expect(getImpersonation()).toBeNull();
  });

  it("setImpersonation dispatches a custom event", () => {
    const handler = vi.fn();
    windowStub.addEventListener("pilot:impersonation-change", handler);
    setImpersonation({ tenantId: "tenant-001", tenantName: "Acme Electric" });
    expect(handler).toHaveBeenCalledTimes(1);
    windowStub.removeEventListener("pilot:impersonation-change", handler);
  });

  it("clearImpersonation dispatches a custom event", () => {
    setImpersonation({ tenantId: "tenant-001", tenantName: "Acme Electric" });
    const handler = vi.fn();
    windowStub.addEventListener("pilot:impersonation-change", handler);
    clearImpersonation();
    expect(handler).toHaveBeenCalledTimes(1);
    windowStub.removeEventListener("pilot:impersonation-change", handler);
  });
});
