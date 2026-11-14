/**
 * formatUsPhone — pure US phone formatting utilities (platform-agnostic)
 *
 * Location: packages/ui/src/phone-input/formatUsPhone.ts
 *
 * PLP-FIX-4: Shared phone formatting for all 7 web `type="tel"` fields.
 * Hand-rolled — zero npm deps (rules §8). Display is progressive
 * `(XXX) XXX-XXXX`; emitted value is E.164 `+1XXXXXXXXXX` or `null`.
 */

/**
 * Strip non-digits from raw input. When the result is 11 digits and starts
 * with a US country code `1`, drop the leading `1`. Cap at 10 digits.
 *
 * Examples:
 *   "abc5551234567"      → "5551234567"
 *   "15551234567"        → "5551234567"   (11-digit leading-1 normalize)
 *   "+13025551234"       → "3025551234"
 *   "555"                → "555"
 *   ""                   → ""
 */
export function normalizeUsPhoneDigits(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("1")) {
    return digits.slice(1, 11);
  }
  return digits.slice(0, 10);
}

/**
 * Progressive display formatting:
 *   0–3 digits  → plain digits          "555"
 *   4–6 digits  → "(XXX) YYY"           "(555) 123"
 *   7–10 digits → "(XXX) YYY-ZZZZ"      "(555) 123-4567"
 *
 * Empty input → "".
 */
export function formatUsPhoneDisplay(digits: string): string {
  const d = normalizeUsPhoneDigits(digits);
  if (d.length === 0) return "";
  if (d.length <= 3) return d;
  if (d.length <= 6) return `(${d.slice(0, 3)}) ${d.slice(3)}`;
  return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6, 10)}`;
}

/**
 * Convert digit string to E.164. Returns `+1XXXXXXXXXX` when exactly 10
 * digits are present; otherwise `null` (partial or empty).
 */
export function usPhoneToE164(digits: string): string | null {
  const d = normalizeUsPhoneDigits(digits);
  if (d.length === 10) {
    return `+1${d}`;
  }
  return null;
}
