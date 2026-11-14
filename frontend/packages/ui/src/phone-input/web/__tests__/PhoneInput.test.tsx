/**
 * PhoneInput unit tests — PLP-FIX-4
 *
 * Location: packages/ui/src/phone-input/web/__tests__/PhoneInput.test.tsx
 *
 * Tests progressive formatting, letter stripping, 11-digit leading-1 normalize,
 * backspace re-formatting, blur E.164 emission, partial blur null emission,
 * mount from E.164, and paste of formatted string.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { PhoneInput } from "../PhoneInput";

describe("PhoneInput", () => {
  it("renders empty on mount with empty value", () => {
    render(<PhoneInput id="test" value="" onChange={vi.fn()} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    expect(input.value).toBe("");
  });

  it("mounts from E.164 and displays formatted", () => {
    render(<PhoneInput id="test" value="+15551234567" onChange={vi.fn()} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    expect(input.value).toBe("(555) 123-4567");
  });

  it("mounts from 10 digits and displays formatted", () => {
    render(<PhoneInput id="test" value="5551234567" onChange={vi.fn()} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    expect(input.value).toBe("(555) 123-4567");
  });

  it("progressive format as you type — 3 digits plain", () => {
    render(<PhoneInput id="test" value="" onChange={vi.fn()} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "555" } });
    expect(input.value).toBe("555");
  });

  it("progressive format as you type — 6 digits", () => {
    render(<PhoneInput id="test" value="" onChange={vi.fn()} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "555123" } });
    expect(input.value).toBe("(555) 123");
  });

  it("progressive format as you type — 10 digits", () => {
    render(<PhoneInput id="test" value="" onChange={vi.fn()} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "5551234567" } });
    expect(input.value).toBe("(555) 123-4567");
  });

  it("strips letters from input", () => {
    render(<PhoneInput id="test" value="" onChange={vi.fn()} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "abc555def123ghi4567jkl" } });
    expect(input.value).toBe("(555) 123-4567");
  });

  it("normalizes 11-digit leading-1 to 10 digits", () => {
    render(<PhoneInput id="test" value="" onChange={vi.fn()} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "15551234567" } });
    expect(input.value).toBe("(555) 123-4567");
  });

  it("backspace re-formats from digits", () => {
    render(<PhoneInput id="test" value="" onChange={vi.fn()} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    // Type 10 digits
    fireEvent.change(input, { target: { value: "5551234567" } });
    expect(input.value).toBe("(555) 123-4567");
    // Backspace: remove last digit → 9 digits
    fireEvent.change(input, { target: { value: "(555) 123-456" } });
    expect(input.value).toBe("(555) 123-456");
  });

  it("blur with 10 digits emits E.164", () => {
    const onChange = vi.fn();
    render(<PhoneInput id="test" value="" onChange={onChange} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "5551234567" } });
    fireEvent.blur(input);
    expect(onChange).toHaveBeenLastCalledWith("+15551234567");
  });

  it("blur with partial digits emits null", () => {
    const onChange = vi.fn();
    render(<PhoneInput id="test" value="" onChange={onChange} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "555123" } });
    fireEvent.blur(input);
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("blur with empty emits null", () => {
    const onChange = vi.fn();
    render(<PhoneInput id="test" value="" onChange={onChange} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.blur(input);
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("paste of formatted (555) 123-4567 works", () => {
    const onChange = vi.fn();
    render(<PhoneInput id="test" value="" onChange={onChange} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.paste(input, {
      clipboardData: { getData: () => "(555) 123-4567" },
    });
    expect(input.value).toBe("(555) 123-4567");
    expect(onChange).toHaveBeenLastCalledWith("+15551234567");
  });

  it("onChange emits E.164 eagerly when 10 digits reached", () => {
    const onChange = vi.fn();
    render(<PhoneInput id="test" value="" onChange={onChange} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "5551234567" } });
    expect(onChange).toHaveBeenLastCalledWith("+15551234567");
  });

  it("onChange emits null for partial input", () => {
    const onChange = vi.fn();
    render(<PhoneInput id="test" value="" onChange={onChange} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "555" } });
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("passes aria-invalid and aria-describedby through", () => {
    render(
      <PhoneInput
        id="test"
        value=""
        onChange={vi.fn()}
        ariaInvalid
        ariaDescribedby="error-msg"
      />,
    );
    const input = screen.getByRole("textbox") as HTMLInputElement;
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAttribute("aria-describedby", "error-msg");
  });
});
