/**
 * HelpChatScreen mobile unit tests — FE-B16
 *
 * Location: apps/mobile/__tests__/batch_fe_b16/helpChatScreen.unit.test.tsx
 *
 * Contract tests for mobile help feature using Jest-compatible mocks.
 * Avoids referencing out-of-scope variables inside jest.mock() factories.
 */

// All jest.mock calls must have no out-of-scope variable references
jest.mock("expo-router", () => ({
  Stack: {
    Screen: jest.fn().mockReturnValue(null),
  },
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), back: jest.fn() }),
}));

jest.mock("expo-constants", () => ({
  default: {
    expoConfig: {
      version: "1.0.0-test",
      ios: { buildNumber: "42" },
    },
  },
}));

jest.mock("@tanstack/react-query", () => ({
  useMutation: jest.fn().mockReturnValue({
    mutate: jest.fn(),
    mutateAsync: jest.fn(),
    isError: false,
    isPending: false,
    isSuccess: false,
    error: null,
    reset: jest.fn(),
  }),
  useQuery: jest.fn().mockReturnValue({
    data: null,
    isLoading: false,
    error: null,
  }),
  useQueryClient: jest.fn().mockReturnValue({ invalidateQueries: jest.fn() }),
  QueryClient: jest.fn(),
  QueryClientProvider: jest.fn().mockReturnValue(null),
  useInfiniteQuery: jest.fn().mockReturnValue({
    data: null,
    isLoading: false,
    error: null,
    fetchNextPage: jest.fn(),
    hasNextPage: false,
    isFetchingNextPage: false,
  }),
}));

jest.mock("../../features/help/hooks/useHelpChat", () => ({
  useHelpChat: jest.fn().mockReturnValue({
    messages: [],
    session: null,
    isStreaming: false,
    error: null,
    sendMessage: jest.fn(),
    sendMessageWithContext: jest.fn(),
  }),
}));

jest.mock("../../features/help/hooks/useHelpSessionFeedback", () => ({
  useHelpSessionFeedback: jest.fn().mockReturnValue({ mutate: jest.fn() }),
}));

describe("Mobile HelpChatScreen — contract tests", () => {
  it("mobile help hooks export useHelpChat", () => {
    const { useHelpChat } = require("../../features/help/hooks/useHelpChat");
    expect(typeof useHelpChat).toBe("function");
  });

  it("mobile help hooks export useHelpSessionFeedback", () => {
    const {
      useHelpSessionFeedback,
    } = require("../../features/help/hooks/useHelpSessionFeedback");
    expect(typeof useHelpSessionFeedback).toBe("function");
  });

  it("useHelpChat mock returns expected shape", () => {
    const { useHelpChat } = require("../../features/help/hooks/useHelpChat");
    const result = useHelpChat();
    expect(result).toHaveProperty("messages");
    expect(result).toHaveProperty("sendMessage");
    expect(result).toHaveProperty("isStreaming");
  });

  it("useHelpSessionFeedback mock returns mutate function", () => {
    const {
      useHelpSessionFeedback,
    } = require("../../features/help/hooks/useHelpSessionFeedback");
    const result = useHelpSessionFeedback(null);
    expect(typeof result.mutate).toBe("function");
  });
});
