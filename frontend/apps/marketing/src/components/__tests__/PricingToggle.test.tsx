import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PricingToggle from "../PricingToggle";

describe("PricingToggle", () => {
  it("defaults to Monthly selected", () => {
    const onToggle = vi.fn();
    render(<PricingToggle onToggle={onToggle} />);

    const monthly = screen.getByRole("radio", { name: /monthly/i });
    const annual = screen.getByRole("radio", { name: /annual/i });

    expect(monthly).toHaveAttribute("aria-checked", "true");
    expect(annual).toHaveAttribute("aria-checked", "false");
  });

  it("switches to Annual on click and calls onToggle", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(<PricingToggle onToggle={onToggle} />);

    const annual = screen.getByRole("radio", { name: /annual/i });
    await user.click(annual);

    expect(annual).toHaveAttribute("aria-checked", "true");
    expect(onToggle).toHaveBeenCalledWith("annual");
  });

  it("switches back to Monthly on click", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(<PricingToggle onToggle={onToggle} />);

    const annual = screen.getByRole("radio", { name: /annual/i });
    await user.click(annual);
    expect(onToggle).toHaveBeenLastCalledWith("annual");

    const monthly = screen.getByRole("radio", { name: /monthly/i });
    await user.click(monthly);
    expect(onToggle).toHaveBeenLastCalledWith("monthly");
    expect(monthly).toHaveAttribute("aria-checked", "true");
  });

  it("has radiogroup role with aria-label", () => {
    render(<PricingToggle onToggle={vi.fn()} />);
    const group = screen.getByRole("radiogroup");
    expect(group).toHaveAttribute("aria-label", "Billing interval");
  });

  it("supports arrow key navigation", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(<PricingToggle onToggle={onToggle} />);

    const monthly = screen.getByRole("radio", { name: /monthly/i });
    monthly.focus();

    // ArrowRight should select Annual
    await user.keyboard("{ArrowRight}");
    expect(onToggle).toHaveBeenLastCalledWith("annual");

    // ArrowLeft should select Monthly
    await user.keyboard("{ArrowLeft}");
    expect(onToggle).toHaveBeenLastCalledWith("monthly");
  });

  it("shows the save hint text", () => {
    render(<PricingToggle onToggle={vi.fn()} />);
    expect(screen.getByText(/Save ~17% with annual/)).toBeInTheDocument();
  });

  it("respects controlled value prop", () => {
    render(<PricingToggle onToggle={vi.fn()} value="annual" />);

    const annual = screen.getByRole("radio", { name: /annual/i });
    const monthly = screen.getByRole("radio", { name: /monthly/i });

    expect(annual).toHaveAttribute("aria-checked", "true");
    expect(monthly).toHaveAttribute("aria-checked", "false");
  });
});
