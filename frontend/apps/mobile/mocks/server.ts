/**
 * MSW Node server setup — mobile (React Native / Jest test environment)
 *
 * Location: apps/mobile/mocks/server.ts
 *
 * Used in Jest tests via setupFilesAfterFramework.
 * Activated when EXPO_PUBLIC_USE_MSW_MOCKS=true in test environment.
 */

import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
