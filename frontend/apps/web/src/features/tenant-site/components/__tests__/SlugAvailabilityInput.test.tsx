/**
 * SlugAvailabilityInput — Unit Tests
 *
 * Location: apps/web/src/features/tenant-site/components/__tests__/SlugAvailabilityInput.test.tsx
 *
 * Tests URL display, locked state, availability feedback states.
 * Uses MSW for the slug-availability endpoint.
 *
 * RULE 14: retry: false QueryClient. RULE 15: server.resetHandlers in afterEach.
 */

import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import React from "react";
import { tenantSiteHandlers } from "../../../../mocks/handlers/tenantSiteHandlers";
import { SlugAvailabilityInput } from "../SlugAvailabilityInput";

const server = setupServer(...tenantSiteHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("SlugAvailabilityInput", () => {
  it("renders URL prefix and suffix around the input", () => {
    renderWithProviders(<SlugAvailabilityInput value="" onChange={vi.fn()} />);
    expect(screen.getByText("https://")).toBeInTheDocument();
    expect(screen.getByTestId("site-slug-input")).toBeInTheDocument();
  });

  it("shows helper text when value is empty", () => {
    renderWithProviders(<SlugAvailabilityInput value="" onChange={vi.fn()} />);
    expect(
      screen.getByText(/Lowercase letters, numbers, and hyphens/),
    ).toBeInTheDocument();
  });

  it("shows locked state when locked=true", () => {
    renderWithProviders(
      <SlugAvailabilityInput
        value="my-shop"
        onChange={vi.fn()}
        locked={true}
      />,
    );
    const input = screen.getByTestId("site-slug-input") as HTMLInputElement;
    expect(input).toBeDisabled();
    expect(
      screen.getByText(/Slug is locked after first publish/),
    ).toBeInTheDocument();
  });

  it("shows Available feedback for a valid slug after debounce", async () => {
    renderWithProviders(
      <SlugAvailabilityInput value="my-shop" onChange={vi.fn()} />,
    );

    // Wait for debounce (300ms) + fetch
    await waitFor(
      () => {
        expect(screen.getByText("Available")).toBeInTheDocument();
      },
      { timeout: 2000 },
    );
  });

  it("shows taken feedback with suggestion for taken slug", async () => {
    renderWithProviders(
      <SlugAvailabilityInput value="taken" onChange={vi.fn()} />,
    );

    await waitFor(
      () => {
        expect(screen.getByText("This slug is taken")).toBeInTheDocument();
      },
      { timeout: 2000 },
    );
  });

  it("shows reserved feedback for reserved slug", async () => {
    renderWithProviders(
      <SlugAvailabilityInput value="admin" onChange={vi.fn()} />,
    );

    await waitFor(
      () => {
        expect(screen.getByText("This slug is reserved")).toBeInTheDocument();
      },
      { timeout: 2000 },
    );
  });

  it("calls onChange with lowercased value", () => {
    const onChange = vi.fn();
    renderWithProviders(<SlugAvailabilityInput value="" onChange={onChange} />);
    const input = screen.getByTestId("site-slug-input");
    fireEvent.change(input, { target: { value: "MY-SHOP" } });
    expect(onChange).toHaveBeenCalledWith("my-shop");
  });

  it("calls onAvailabilityChange when availability resolves", async () => {
    const onAvailabilityChange = vi.fn();
    renderWithProviders(
      <SlugAvailabilityInput
        value="my-shop"
        onChange={vi.fn()}
        onAvailabilityChange={onAvailabilityChange}
      />,
    );

    await waitFor(
      () => {
        expect(onAvailabilityChange).toHaveBeenCalledWith(true);
      },
      { timeout: 2000 },
    );
  });
});
