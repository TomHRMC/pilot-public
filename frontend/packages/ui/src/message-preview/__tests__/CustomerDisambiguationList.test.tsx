/**
 * Unit tests — CustomerDisambiguationList
 *
 * Location: packages/ui/src/message-preview/__tests__/CustomerDisambiguationList.test.tsx
 * Runs in @pilot/ui vitest environment.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { CustomerDisambiguationList } from "../CustomerDisambiguationList";
import type { CustomerMatch } from "../types";

const MATCHES: CustomerMatch[] = [
  {
    id: "cust-001",
    name: "Mike Johnson",
    preferred_channel: "sms",
    address: "+15551111111",
  },
  {
    id: "cust-002",
    name: "Sarah Johnson",
    preferred_channel: "email",
    address: "sarah@example.com",
  },
];

describe("CustomerDisambiguationList — rendering", () => {
  it("8. renders all matching customers", () => {
    render(
      <CustomerDisambiguationList
        matches={MATCHES}
        onSelect={vi.fn()}
        query="Johnson"
      />,
    );
    expect(screen.getByText("Mike Johnson")).toBeInTheDocument();
    expect(screen.getByText("Sarah Johnson")).toBeInTheDocument();
  });

  it("9. renders disambiguation prompt with query", () => {
    render(
      <CustomerDisambiguationList
        matches={MATCHES}
        onSelect={vi.fn()}
        query="Johnson"
      />,
    );
    expect(
      screen.getByText((_, element) => {
        return element?.textContent === 'Which "Johnson" did you mean?';
      }),
    ).toBeInTheDocument();
  });

  it("10. calls onSelect with tapped customer", () => {
    const onSelect = vi.fn();
    render(
      <CustomerDisambiguationList
        matches={MATCHES}
        onSelect={onSelect}
        query="Johnson"
      />,
    );
    fireEvent.click(screen.getByTestId("disambiguation-item-cust-001"));
    expect(onSelect).toHaveBeenCalledWith(MATCHES[0]);
  });

  it("11. renders SMS preferred label for sms channel customer", () => {
    render(
      <CustomerDisambiguationList
        matches={MATCHES}
        onSelect={vi.fn()}
        query="Johnson"
      />,
    );
    expect(screen.getByText("SMS preferred")).toBeInTheDocument();
  });

  it("12. renders Email preferred label for email channel customer", () => {
    render(
      <CustomerDisambiguationList
        matches={MATCHES}
        onSelect={vi.fn()}
        query="Johnson"
      />,
    );
    expect(screen.getByText("Email preferred")).toBeInTheDocument();
  });
});
