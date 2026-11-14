/**
 * MSW WebSocket handler — voice stream (mobile, DEV-RUNTIME ONLY)
 *
 * Location: apps/mobile/mocks/handlers/voice.ws.ts
 *
 * ⚠️ Dev-runtime only. NEVER import this module from the Jest barrel
 * (`mocks/handlers/index.ts`) or any Jest test — `ws.link()` instantiates at
 * module-evaluation time and poisons the Node/jsdom environment
 * (TEST-UPLIFT-1C §G Q1 root cause). The Jest barrel (`index.ts`) is HTTP-only;
 * `mocks/browser.ts` composes this handler itself for the dev runtime.
 *
 * Implements the 8-event happy-path sequence from Decision 8 in the design doc.
 * WebSocket endpoint: /api/v1/voice/stream cannot be described in OpenAPI 3.1.
 * Uses MSW 2.x ws.link(...).addEventListener('connection', ...) pattern.
 */

import { ws } from "msw";

const WS_URL =
  (typeof process !== "undefined" && process.env?.EXPO_PUBLIC_WS_URL) ||
  "ws://localhost:8000";

const voiceWsLink = ws.link(`${WS_URL}/api/v1/voice/stream`);

export const voiceWsHandler = voiceWsLink.addEventListener(
  "connection",
  // MSW 2.x WebSocketHandlerConnection — typed via inference
  ({ client }) => {
    client.addEventListener("message", async (event) => {
      const raw = typeof event.data === "string" ? event.data : "";
      let msg: { type: string; payload?: unknown };
      try {
        msg = JSON.parse(raw);
      } catch {
        return;
      }

      if (msg.type === "audio_chunk") {
        // Event 1: partial transcript
        await delay(150);
        client.send(
          JSON.stringify({
            type: "transcript_partial",
            payload: { text: "Create a quote for..." },
          }),
        );

        // Event 2: final transcript
        await delay(200);
        client.send(
          JSON.stringify({
            type: "transcript_final",
            payload: { text: "Create a quote for Tom Johnson" },
          }),
        );

        // Event 3: intent detected
        await delay(300);
        client.send(
          JSON.stringify({
            type: "intent_detected",
            payload: {
              intent_type: "create_quote",
              entities: { customer_name: "Tom Johnson" },
            },
          }),
        );

        // Event 4: response streaming
        await delay(100);
        client.send(
          JSON.stringify({
            type: "response_streaming",
            payload: {
              text: "Matched Tom Johnson at 42 Oak Street. Different one?",
            },
          }),
        );

        // Event 5: response final with quote_preview (live mode)
        await delay(200);
        client.send(
          JSON.stringify({
            type: "response_final",
            payload: {
              message_id: "msg-ws-001",
              text: "Matched Tom Johnson at 42 Oak Street. Different one?",
              structured_content: {
                render_mode: "live",
                content_type: "quote_preview",
                entity_id: "q-mock-001",
                snapshot_payload: null,
              },
            },
          }),
        );
      }

      if (msg.type === "confirm_intent") {
        // Event 6: action committed with snapshot freeze
        await delay(300);
        client.send(
          JSON.stringify({
            type: "action_committed",
            payload: {
              intent_type: "send_quote",
              quote_id: "q-mock-001",
              snapshot_frozen: true,
            },
          }),
        );
      }
    });
  },
);

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
