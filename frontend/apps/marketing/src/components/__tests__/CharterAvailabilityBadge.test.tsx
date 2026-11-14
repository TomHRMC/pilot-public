import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import CharterAvailabilityBadge from "../CharterAvailabilityBadge";

// Helper to mock the global fetch
function mockFetchResponse(data: unknown, ok = true) {
  return vi.fn().mockResolvedValue({
    ok,
    json: () => Promise.resolve(data),
  });
}

describe("CharterAvailabilityBadge", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders nothing while loading", () => {
    globalThis.fetch = mockFetchResponse({
      open: true,
      remaining: 5,
    }) as never;
    const { container } = render(<CharterAvailabilityBadge />);
    expect(container.firstChild).toBeNull();
  });

  it("shows scarcity count when open and remaining <= 8", async () => {
    globalThis.fetch = mockFetchResponse({
      open: true,
      remaining: 4,
    }) as never;
    render(<CharterAvailabilityBadge />);
    await waitFor(() => {
      expect(screen.getByText(/Only 4 spots remaining/)).toBeInTheDocument();
    });
  });

  it("shows open message when remaining > 8", async () => {
    globalThis.fetch = mockFetchResponse({
      open: true,
      remaining: 11,
    }) as never;
    render(<CharterAvailabilityBadge />);
    await waitFor(() => {
      expect(screen.getByText(/Charter program is open/)).toBeInTheDocument();
    });
  });

  it("shows full message when open is false", async () => {
    globalThis.fetch = mockFetchResponse({
      open: false,
      remaining: 0,
    }) as never;
    render(<CharterAvailabilityBadge />);
    await waitFor(() => {
      expect(screen.getByText(/Charter program is full/)).toBeInTheDocument();
    });
  });

  it("shows full message when remaining is 0 but open is true", async () => {
    globalThis.fetch = mockFetchResponse({
      open: true,
      remaining: 0,
    }) as never;
    render(<CharterAvailabilityBadge />);
    await waitFor(() => {
      expect(screen.getByText(/Charter program is full/)).toBeInTheDocument();
    });
  });

  it("renders nothing on fetch error (fail silently)", async () => {
    globalThis.fetch = vi
      .fn()
      .mockRejectedValue(new Error("Network error")) as never;
    const { container } = render(<CharterAvailabilityBadge />);
    // Wait a tick for the promise to reject
    await waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });

  it("renders nothing on non-ok response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({}),
    }) as never;
    const { container } = render(<CharterAvailabilityBadge />);
    await waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });

  it("has role=status and aria-live=polite for screen reader announcements", async () => {
    globalThis.fetch = mockFetchResponse({
      open: true,
      remaining: 3,
    }) as never;
    render(<CharterAvailabilityBadge />);
    await waitFor(() => {
      const status = screen.getByRole("status");
      expect(status).toHaveAttribute("aria-live", "polite");
    });
  });
});
