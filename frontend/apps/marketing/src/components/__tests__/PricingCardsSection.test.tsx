import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PricingCardsSection from "../PricingCardsSection";

describe("PricingCardsSection", () => {
  it("renders Starter and Teams cards with monthly prices by default", () => {
    render(<PricingCardsSection />);

    expect(screen.getByText("Starter")).toBeInTheDocument();
    expect(screen.getByText("Teams")).toBeInTheDocument();
    expect(screen.getByText("$59")).toBeInTheDocument();
    expect(screen.getByText("$179")).toBeInTheDocument();
  });

  it("shows annual subtext under monthly prices", () => {
    render(<PricingCardsSection />);

    expect(screen.getByText("or $49/mo billed annually")).toBeInTheDocument();
    expect(screen.getByText("or $149/mo billed annually")).toBeInTheDocument();
  });

  it("switches to annual prices when Annual is clicked", async () => {
    const user = userEvent.setup();
    render(<PricingCardsSection />);

    const annual = screen.getByRole("radio", { name: /annual/i });
    await user.click(annual);

    // Annual prices should now be visible
    expect(screen.getByText("$49")).toBeInTheDocument();
    expect(screen.getByText("$149")).toBeInTheDocument();
    expect(screen.getByText("billed $588/year")).toBeInTheDocument();
    expect(screen.getByText("billed $1788/year")).toBeInTheDocument();
  });

  it("switches back to monthly prices when Monthly is clicked", async () => {
    const user = userEvent.setup();
    render(<PricingCardsSection />);

    // Switch to annual
    const annual = screen.getByRole("radio", { name: /annual/i });
    await user.click(annual);
    expect(screen.getByText("billed $588/year")).toBeInTheDocument();

    // Switch back to monthly
    const monthly = screen.getByRole("radio", { name: /monthly/i });
    await user.click(monthly);
    expect(screen.getByText("$59")).toBeInTheDocument();
    expect(screen.getByText("or $49/mo billed annually")).toBeInTheDocument();
  });

  it("renders the pricing toggle with radiogroup role", () => {
    render(<PricingCardsSection />);
    const group = screen.getByRole("radiogroup");
    expect(group).toHaveAttribute("aria-label", "Billing interval");
  });

  it("renders Start Free Trial links for both plans", () => {
    render(<PricingCardsSection />);
    const links = screen.getAllByText("Start Free Trial");
    expect(links).toHaveLength(2);
  });
});
