/**
 * HelpAnchor barrel — platform-resolved — FE-B16
 *
 * Location: packages/ui/src/help-anchor/index.ts
 *
 * Web builds import from web/HelpAnchor; mobile from mobile/HelpAnchor.
 * Both share the same HelpAnchorProps interface (types.ts).
 *
 * NOTE: The platform resolution (.native.ts / .ts) pattern is used here.
 * This file (index.ts) is the web default.
 * The mobile build resolves index.native.ts (created separately).
 */

export { HelpAnchor } from "./web/HelpAnchor";
export type {
  HelpAnchorProps,
  HelpContextPayload,
  HelpActionType,
} from "./types";
