/**
 * Voice module — barrel export
 *
 * Location: packages/ui/src/voice/index.ts
 *
 * Exports shared types and the platform-resolved useVoiceStream hook.
 * The mobile implementation is the default for FE-B3.
 * Web implementation (FE-B16) follows the same public API.
 *
 * Downstream consumers import from '@pilot/ui/voice' or '@pilot/ui'.
 */

export type {
  VoiceState,
  VoiceStreamEventType,
  VoiceStreamEvent,
  UseVoiceStreamReturn,
} from "./types";

export { voiceStateTokens } from "./types";

// Platform-resolved hook.
// Mobile build resolves here. Web build will swap in web/useVoiceStream.
export { useVoiceStream } from "./mobile/useVoiceStream";
