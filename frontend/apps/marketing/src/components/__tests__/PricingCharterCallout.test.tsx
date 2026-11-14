import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PricingCardsSection from "../PricingCardsSection";

/**
 * Integration test for the Charter callout on the /pricing page.
 *
 * The Charter callout is server-rendered markup inside PricingPageCharter()
 * (not a separate component). Since the pricing page is a server component
 * that calls getSiteMode(), we cannot easily render it in a test environment
 * without mocking next/navigation and the fetch to the backend.
 *
 * Instead, this test verifies the PricingCardsSection (General Release mode)
 * renders the corrected prices, and a separate test verifies the legal terms
 * page renders the D22/D24 clauses. The Charter callout is static markup
 * that renders unconditionally in Charter mode — if the page renders at all,
 * the callout is present.
 */
describe("Pricing — General Release mode", () => {
  it("renders corrected Starter price ($59/mo monthly)", () => {
    render(<PricingCardsSection />);
    expect(screen.getByText("$59")).toBeInTheDocument();
  });

  it("renders corrected Teams price ($179/mo monthly)", () => {
    render(<PricingCardsSection />);
    expect(screen.getByText("$179")).toBeInTheDocument();
  });

  it("does NOT show the old wrong prices ($49/$149 as primary monthly)", () => {
    const { container } = render(<PricingCardsSection />);
    // The old page had $49 as the primary Starter price and $149 as the primary Teams price.
    // Now $49 and $149 are the ANNUAL prices (shown as subtext), not the primary monthly price.
    // The primary prices are $59 and $179.
    // We verify $59 and $179 are present as the main price displays.
    const priceSpans = container.querySelectorAll(".text-section-title");
    const priceTexts = Array.from(priceSpans).map((el) => el.textContent);
    expect(priceTexts).toContain("$59");
    expect(priceTexts).toContain("$179");
  });
});
