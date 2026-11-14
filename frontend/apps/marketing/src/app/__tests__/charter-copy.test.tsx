/**
 * MKT-B12 content-guard test for /charter
 *
 * Guards the two highest-risk team-voice regressions:
 *   (a) "reviewed personally by our team" copy is present
 *   (b) "Tom reviews" first-person copy is absent
 *
 * The charter page is an async server component that calls getSiteMode()
 * and redirect(). We mock both so the page renders in Charter mode without
 * redirecting. CharterApplicationForm and CharterAvailabilityBadge are
 * mocked to avoid Turnstile / fetch complexity — this test guards copy,
 * not form behavior.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock getSiteMode → Charter mode (no redirect to /sign-up)
vi.mock("../../../lib/useSiteMode", () => ({
  getSiteMode: vi.fn().mockResolvedValue({
    mode: "charter",
    isCharterMode: true,
    isGeneralRelease: false,
  }),
}));

// Mock next/navigation redirect (should not be called in Charter mode)
vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
}));

// Mock CharterApplicationForm (client component — Turnstile complexity)
vi.mock("../../../components/forms/CharterApplicationForm", () => ({
  default: () => <div data-testid="charter-form-mock">Charter form mock</div>,
}));

// Mock CharterAvailabilityBadge (client component — fetches backend)
vi.mock("../../../components/CharterAvailabilityBadge", () => ({
  default: () => <div data-testid="badge-mock">Badge mock</div>,
}));

// Import the page AFTER mocks are registered
import CharterPage from "../charter/page";

describe("MKT-B12 — /charter team-voice content guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders team-voice copy: 'reviewed personally by our team'", async () => {
    const ui = await CharterPage();
    render(ui);
    // Item 21/30 — "Each signup is reviewed personally by our team" (appears twice: form-adjacent + footer)
    expect(
      screen.getAllByText(/reviewed personally by our team/i).length,
    ).toBeGreaterThanOrEqual(1);
  });

  it("does NOT render first-person 'Tom reviews' copy", async () => {
    const ui = await CharterPage();
    render(ui);
    expect(screen.queryByText(/Tom reviews/i)).toBeNull();
  });

  it("renders team-voice hero H1: 'We're filling them now'", async () => {
    const ui = await CharterPage();
    render(ui);
    expect(screen.getByText(/We.*re filling them now/i)).toBeInTheDocument();
  });

  it("does NOT render first-person hero 'I'm filling them now'", async () => {
    const ui = await CharterPage();
    render(ui);
    expect(screen.queryByText(/I.*m filling them now/i)).toBeNull();
  });

  it("renders team-voice exit guarantee H2: 'we'll help you leave'", async () => {
    const ui = await CharterPage();
    render(ui);
    expect(screen.getByText(/we.*ll help you leave/i)).toBeInTheDocument();
  });

  it("renders team-voice theAsk heading: 'What we need from you'", async () => {
    const ui = await CharterPage();
    render(ui);
    expect(screen.getByText(/What we need from you/i)).toBeInTheDocument();
  });

  it("renders the founder bio callout (no 'I designed this myself')", async () => {
    const ui = await CharterPage();
    render(ui);
    // Item 26 — bio callout with the author's engineering background
    expect(
      screen.getByText(/fifteen years in electrical and controls/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/I designed this myself/i)).toBeNull();
  });
});
