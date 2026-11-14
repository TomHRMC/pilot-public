/**
 * MSW Browser Service Worker factory — web dev only
 *
 * Location: apps/mobile/mocks/browser.ts
 *
 * Exports a startWorker() function (NOT a pre-constructed worker) so that
 * setupWorker() is called lazily at runtime — never at module evaluation time.
 *
 * IMPORTANT: setupWorker() must NOT be called at module level because Metro's
 * SSR/node renderer (node/render.js) also evaluates this module in a Node.js
 * context where `window` is undefined, causing:
 *   "[MSW] Failed to execute `setupWorker` in a non-browser environment"
 *
 * Callers (app/_layout.tsx) must guard with:
 *   if (Platform.OS === 'web' && typeof window !== 'undefined') { ... }
 */

import { handlers } from "./handlers";
import { voiceWsHandler } from "./handlers/voice.ws";

export async function startMockServiceWorker(
  options?: Record<string, unknown>,
): Promise<void> {
  // Dynamic import of setupWorker so Metro can tree-shake this
  // on native platforms (dead code after Platform.OS check at call site).
  const { setupWorker } = await import("msw/browser");
  // Compose the WS handler here (dev-runtime only) — the Jest barrel
  // (handlers/index.ts) is HTTP-only so it stays Jest-safe.
  // See TEST-UPLIFT-1C §F.1 / §G Q1 for the isolation rationale.
  const worker = setupWorker(...handlers, voiceWsHandler);
  await worker.start(options ?? { onUnhandledRequest: "bypass" });
}
