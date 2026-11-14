import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QUOTA_HARD_BLOCKED } from "../../features/customer-comms/mocks/customerCommsFixtures";
import { ReplyComposer } from "../../features/customer-comms/components/ReplyComposer";

const server = setupServer(
  http.get("*/api/v1/sms/quota", () => {
    console.log("MSW intercepted /api/v1/sms/quota in hard-block");
    return HttpResponse.json(QUOTA_HARD_BLOCKED);
  }),
);

let qc: QueryClient;

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  qc?.clear();
});
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("mobile-quota-hard-block integration", () => {
  it("hard cap at 100%: send button disabled after quota loads", async () => {
    render(
      <ReplyComposer
        threadId="thread-001"
        customerId="customer-001"
        testID="composer"
      />,
      { wrapper },
    );

    const input = screen.getByTestId("composer-text-input");
    fireEvent.changeText(input, "Hello");

    await waitFor(
      () => {
        const sendBtn = screen.getByTestId("send-button");
        expect(sendBtn.props.accessibilityState?.disabled).toBe(true);
      },
      { timeout: 2000 },
    );
  });
});
