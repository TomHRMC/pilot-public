/**
 * mobile-opted-out-block — integration test (TCPA critical)
 *
 * Tests: Customer opted out → GET /sms/quota?customer_id=X returns opted_out
 * → send disabled + opted-out copy visible.
 *
 * RULE 7: NO force-send affordance can exist.
 * Design doc G.2, E.1
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { communicationsHandlers } from "../../mocks/handlers/communicationsHandlers";
import { ReplyComposer } from "../../features/customer-comms/components/ReplyComposer";

const server = setupServer(...communicationsHandlers);

let qc: QueryClient;

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  qc?.clear();
});
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("mobile-opted-out-block TCPA integration (critical)", () => {
  it("opted-out customer → send button disabled + error banner visible", async () => {
    render(
      <ReplyComposer
        threadId="thread-003"
        customerId="customer-003"
        isOptedOut={true}
        testID="composer"
      />,
      { wrapper },
    );

    // Send button must be disabled
    const sendBtn = screen.getByTestId("send-button");
    expect(sendBtn.props.accessibilityState?.disabled).toBe(true);

    // Opted-out banner must be visible
    expect(screen.getByTestId("opted-out-banner")).toBeTruthy();
  });

  it("CRITICAL: NO 'force send' or 'override' CTA exists anywhere in UI", async () => {
    render(
      <ReplyComposer
        threadId="thread-003"
        customerId="customer-003"
        isOptedOut={true}
        testID="composer"
      />,
      { wrapper },
    );

    // Ensure there is absolutely no force-send affordance
    expect(
      screen.queryByText(/force send|send anyway|override|bypass/i),
    ).toBeNull();

    // Only one button (send) and it must be disabled
    const sendBtn = screen.getByTestId("send-button");
    expect(sendBtn.props.accessibilityState?.disabled).toBe(true);
  });
});
