/**
 * MSW browser worker setup — web
 *
 * Location: apps/web/src/mocks/browser.ts
 *
 * Creates and exports the MSW ServiceWorker instance for browser dev use.
 * Activated in RootProviders when NEXT_PUBLIC_USE_MSW_MOCKS=true.
 *
 * The worker file (mockServiceWorker.js) must be present at /public/mockServiceWorker.js.
 * Generate it by running: npx msw init public/ --save
 */

import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

export const worker = setupWorker(...handlers);
