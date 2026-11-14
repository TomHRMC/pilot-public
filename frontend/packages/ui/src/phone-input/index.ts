/**
 * phone-input — Public API barrel
 * Location: packages/ui/src/phone-input/index.ts
 *
 * PLP-FIX-4: Shared US phone input + pure formatting utilities.
 * Web-only component (RN variant deferred). Util is platform-agnostic.
 */

export { PhoneInput } from "./web/PhoneInput";
export type { PhoneInputProps } from "./web/PhoneInput";
export {
  normalizeUsPhoneDigits,
  formatUsPhoneDisplay,
  usPhoneToE164,
} from "./formatUsPhone";
