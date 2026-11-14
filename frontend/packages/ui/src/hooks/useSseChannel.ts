/**
 * useSseChannel — Server-Sent Events Hook
 *
 * Location: packages/ui/src/hooks/useSseChannel.ts
 * Exported from: packages/ui/src/hooks/index.ts + packages/ui/src/index.ts
 *
 * Established in FE-B4 (dispatch board stream).
 * Consumed by FE-B8 (calendar conflicts), FE-B10 (SMS threads), FE-B12 (notifications).
 *
 * Pattern ref: mvp-arch.md §13.11; pilot-react-engineer-methods.md §10.4
 *
 * Platform: Web-only (native EventSource). See MOBILE EXTENSION NOTE below.
 *
 * MOBILE EXTENSION NOTE (FE-B10 or later):
 * Mobile does not support native EventSource. If useSseChannel is needed on mobile,
 * replace the eventSourceFactory default with react-native-sse:
 *   import EventSource from 'react-native-sse';
 * The public API is identical; only the factory differs.
 * Pattern: packages/ui/src/voice/ web/mobile split for reference.
 *
 * ⚠️ INTERFACE LOCKED — changes require downstream impact review for
 * FE-B8, FE-B10, FE-B12. See batch-fe-b4-design.md §F.3 §G.4.
 */

import { useCallback, useEffect, useRef, useState } from "react";

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface SseMessage {
  /** SSE event `id` field (used for Last-Event-ID reconnection header) */
  id?: string;
  /** SSE event `event` field (the named event type) */
  type?: string;
  /** SSE event `data` field (raw string — parse as JSON in onMessage) */
  data: string;
}

export interface UseSseChannelOptions {
  /**
   * The SSE endpoint path (without origin). JWT is appended as ?token= query param.
   * Example: '/api/v1/schedule/board/stream'
   */
  path: string;

  /**
   * Called for each received SSE message. Parse event.data as JSON for structured events.
   * SSE messages carry cache-invalidation cues, NOT full payloads.
   */
  onMessage: (message: SseMessage) => void;

  /**
   * If set (milliseconds), the hook falls back to polling at this interval
   * when the EventSource connection fails or is unsupported.
   * Polling calls `pollFn` — if pollFn is omitted, fallback polling is a no-op.
   * Recommended: 60_000 (60 seconds) per mvp-arch.md §13.11.
   */
  fallbackToPollingMs?: number;

  /**
   * Optional polling function invoked when SSE is unavailable.
   * Receives no arguments; should invalidate TanStack Query keys directly.
   */
  pollFn?: () => void;

  /**
   * Whether the channel should be active. Set to false to disconnect
   * (e.g., when tab is backgrounded). Default: true.
   */
  enabled?: boolean;

  /**
   * Retry delay in milliseconds between reconnection attempts.
   * Uses exponential backoff up to this maximum. Default: 60_000.
   */
  maxRetryDelayMs?: number;

  /**
   * Optional factory function for creating EventSource instances.
   * Used for test injection to replace native EventSource with a mock.
   * Default: (url) => new EventSource(url)
   */
  eventSourceFactory?: (url: string) => EventSource;

  /**
   * Optional async function that returns the current JWT string.
   * When provided, the hook calls getToken() before opening the EventSource
   * and appends the result as `?token=<jwt>` to the URL.
   *
   * Browser EventSource cannot set Authorization headers — this is the only
   * supported auth mechanism for SSE endpoints that require authentication.
   *
   * The getter is called on every (re)connection attempt so refreshed tokens
   * are always used. If getToken() rejects, the connection is not opened.
   *
   * BETA-B2: Rule 3 compliance — centralise JWT injection here instead of
   * manually constructing token URLs in each consumer hook.
   *
   * @example
   * useSseChannel({
   *   path: '/api/v1/scheduling/board/stream',
   *   getToken: async () => {
   *     const session = await fetchAuthSession();
   *     return session.tokens?.idToken?.toString() ?? '';
   *   },
   *   onMessage: handler,
   * });
   */
  getToken?: () => Promise<string>;
}

export interface UseSseChannelReturn {
  /** True when EventSource is open and receiving messages */
  isConnected: boolean;
  /** True when in fallback polling mode */
  isPolling: boolean;
  /** Last received message, or null */
  lastMessage: SseMessage | null;
  /** Error from last connection attempt, or null */
  connectionError: Event | null;
  /** Manually close the connection */
  disconnect: () => void;
  /** Manually reconnect (resets backoff) */
  reconnect: () => void;
}

// ─── Constants ─────────────────────────────────────────────────────────────────

const INITIAL_RETRY_DELAY_MS = 1_000;
const BACKOFF_MULTIPLIER = 2;
const MAX_FAILED_RECONNECTS_BEFORE_FALLBACK = 3;

// ─── Implementation ────────────────────────────────────────────────────────────

/**
 * Opens a Server-Sent Events channel and calls onMessage for each event.
 * Implements exponential backoff and optional fallback to polling.
 *
 * SSE messages carry "entity changed — refetch" cues ONLY.
 * They do NOT carry full payloads. The hook invalidates TanStack Query cache;
 * the UI refetches. Never process SSE payloads as full entity data.
 *
 * @example
 * const { isConnected } = useSseChannel({
 *   path: '/api/v1/schedule/board/stream',
 *   onMessage: (msg) => {
 *     const event = JSON.parse(msg.data) as SseBoardEvent;
 *     queryClient.invalidateQueries({ queryKey: ['dispatch-board'] });
 *   },
 *   fallbackToPollingMs: 60_000,
 *   pollFn: () => queryClient.invalidateQueries({ queryKey: ['dispatch-board'] }),
 * });
 */
export function useSseChannel(
  options: UseSseChannelOptions,
): UseSseChannelReturn {
  const {
    path,
    onMessage,
    fallbackToPollingMs,
    pollFn,
    enabled = true,
    maxRetryDelayMs = 60_000,
    eventSourceFactory,
    getToken,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [lastMessage, setLastMessage] = useState<SseMessage | null>(null);
  const [connectionError, setConnectionError] = useState<Event | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const retryDelayRef = useRef(INITIAL_RETRY_DELAY_MS);
  const failedAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastEventIdRef = useRef<string | undefined>(undefined);
  const onMessageRef = useRef(onMessage);
  const pollFnRef = useRef(pollFn);
  const getTokenRef = useRef(getToken);

  // Keep refs current without re-running effect
  onMessageRef.current = onMessage;
  pollFnRef.current = pollFn;
  getTokenRef.current = getToken;

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return;
    if (!fallbackToPollingMs) return;

    setIsPolling(true);
    setIsConnected(false);

    pollTimerRef.current = setInterval(() => {
      pollFnRef.current?.();
    }, fallbackToPollingMs);
  }, [fallbackToPollingMs]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const closeEventSource = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const connect = useCallback(() => {
    closeEventSource();
    stopPolling();

    if (!enabled) return;

    // Build URL — if getToken is provided, fetch JWT and append as ?token=<jwt>.
    // Browser EventSource cannot send Authorization headers, so the token must be
    // in the query string (BETA-B2 Rule 3 compliance).
    const apiBase = typeof window !== "undefined" ? window.location.origin : "";
    const lastEventParam = lastEventIdRef.current
      ? `&lastEventId=${encodeURIComponent(lastEventIdRef.current)}`
      : "";

    async function openConnection() {
      let url = `${apiBase}${path}${path.includes("?") ? "&" : "?"}stream=1${lastEventParam}`;

      // If getToken is provided, fetch JWT and append as ?token=<jwt>
      if (getTokenRef.current) {
        try {
          const token = await getTokenRef.current();
          if (token) {
            url = `${url}&token=${encodeURIComponent(token)}`;
          }
        } catch (err) {
          console.error(
            "useSseChannel: getToken() failed — aborting connection",
            err,
          );
          return; // Do not open EventSource without auth
        }
      }

      const factory = eventSourceFactory ?? ((u: string) => new EventSource(u));
      const es = factory(url);
      esRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        retryDelayRef.current = INITIAL_RETRY_DELAY_MS;
        failedAttemptsRef.current = 0;
      };

      es.onmessage = (event: MessageEvent) => {
        const msg: SseMessage = {
          id: event.lastEventId || undefined,
          data: event.data as string,
        };
        if (event.lastEventId) {
          lastEventIdRef.current = event.lastEventId;
        }
        setLastMessage(msg);
        onMessageRef.current(msg);
      };

      // Named event types
      const namedEventHandler = (event: MessageEvent) => {
        const msg: SseMessage = {
          id: event.lastEventId || undefined,
          type: (event as MessageEvent & { type: string }).type,
          data: event.data as string,
        };
        if (event.lastEventId) {
          lastEventIdRef.current = event.lastEventId;
        }
        setLastMessage(msg);
        onMessageRef.current(msg);
      };

      // Common named events used by dispatch board
      const namedEvents = [
        "job_scheduled",
        "job_rescheduled",
        "job_reassigned",
        "job_unassigned",
        "conflict_detected",
        "conflict_cleared",
        "calendar_sync_status",
      ];
      namedEvents.forEach((eventType) => {
        es.addEventListener(eventType, namedEventHandler as EventListener);
      });

      es.onerror = (event: Event) => {
        setIsConnected(false);
        setConnectionError(event);
        es.close();
        esRef.current = null;
        failedAttemptsRef.current += 1;

        // After N failures, fall back to polling
        if (
          fallbackToPollingMs &&
          failedAttemptsRef.current >= MAX_FAILED_RECONNECTS_BEFORE_FALLBACK
        ) {
          startPolling();
          return;
        }

        // Exponential backoff reconnect
        const delay = Math.min(
          retryDelayRef.current * BACKOFF_MULTIPLIER,
          maxRetryDelayMs,
        );
        retryDelayRef.current = delay;

        reconnectTimerRef.current = setTimeout(() => {
          if (enabled) connect();
        }, delay);
      };
    }

    void openConnection();
  }, [
    path,
    enabled,
    eventSourceFactory,
    fallbackToPollingMs,
    maxRetryDelayMs,
    closeEventSource,
    stopPolling,
    startPolling,
  ]);

  // Connect on mount / when options change
  useEffect(() => {
    if (!enabled) {
      closeEventSource();
      stopPolling();
      return;
    }

    connect();

    return () => {
      closeEventSource();
      stopPolling();
    };
  }, [enabled, path, connect, closeEventSource, stopPolling]);

  const disconnect = useCallback(() => {
    closeEventSource();
    stopPolling();
  }, [closeEventSource, stopPolling]);

  const reconnect = useCallback(() => {
    retryDelayRef.current = INITIAL_RETRY_DELAY_MS;
    failedAttemptsRef.current = 0;
    connect();
  }, [connect]);

  return {
    isConnected,
    isPolling,
    lastMessage,
    connectionError,
    disconnect,
    reconnect,
  };
}
