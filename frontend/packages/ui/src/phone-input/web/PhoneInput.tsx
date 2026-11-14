/**
 * PhoneInput — web US phone input with progressive masking
 *
 * Location: packages/ui/src/phone-input/web/PhoneInput.tsx
 *
 * PLP-FIX-4: Shared component for all 7 web `type="tel"` fields.
 * Display: progressive `(XXX) XXX-XXXX` as you type (paste-friendly).
 * Output:  E.164 `+1XXXXXXXXXX` on blur when 10 digits, else `null`.
 *
 * No new npm deps — hand-rolled formatting (rules §8).
 * Visual parity: caller passes the existing INPUT_CLASS via `className`.
 * WCAG 2.2 AA (rules §36): paste works; aria-invalid/aria-describedby passthrough.
 *
 * React Compiler: no hand-memoization (rules §32). State-adjusts-during-render
 * follows the React-recommended "adjusting state when prop changes" pattern.
 */

"use client";

import React, { useState } from "react";
import {
  normalizeUsPhoneDigits,
  formatUsPhoneDisplay,
  usPhoneToE164,
} from "../formatUsPhone";

export interface PhoneInputProps {
  id: string;
  /** E.164 ("+1…"), 10 digits, or "" — all tolerated on mount. */
  value: string;
  /** Emits E.164 when 10 digits; null when cleared or partial. */
  onChange: (e164: string | null) => void;
  onBlur?: () => void;
  disabled?: boolean;
  /** Caller passes the existing INPUT_CLASS — visual parity, no new styling. */
  className?: string;
  autoComplete?: string;
  placeholder?: string;
  ariaInvalid?: boolean;
  ariaDescribedby?: string;
  "data-testid"?: string;
}

export function PhoneInput({
  id,
  value,
  onChange,
  onBlur,
  disabled = false,
  className,
  autoComplete = "tel-national",
  placeholder = "(555) 123-4567",
  ariaInvalid,
  ariaDescribedby,
  ...rest
}: PhoneInputProps) {
  // Internal draft = digits only (≤10 after normalize).
  const [draft, setDraft] = useState(() => normalizeUsPhoneDigits(value));

  // Adjust draft when the parent's `value` prop changes externally (form reset,
  // API hydration). Guard against echo-back: only re-seed when the incoming
  // value represents a genuinely different number than our current draft.
  // This is the React "adjusting state during render" pattern — compiler-safe.
  const [prevValue, setPrevValue] = useState(value);
  if (value !== prevValue) {
    setPrevValue(value);
    const incomingDigits = normalizeUsPhoneDigits(value);
    if (usPhoneToE164(incomingDigits) !== usPhoneToE164(draft)) {
      setDraft(incomingDigits);
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const next = normalizeUsPhoneDigits(e.target.value);
    setDraft(next);
    onChange(usPhoneToE164(next));
  }

  function handleBlur() {
    // Re-emit on blur so a completed 10-digit entry commits E.164 even if
    // onChange already emitted it — idempotent for the parent.
    onChange(usPhoneToE164(draft));
    if (onBlur) onBlur();
  }

  function handlePaste(e: React.ClipboardEvent<HTMLInputElement>) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text");
    const next = normalizeUsPhoneDigits(pasted);
    setDraft(next);
    onChange(usPhoneToE164(next));
  }

  const display = formatUsPhoneDisplay(draft);

  return (
    <input
      id={id}
      type="tel"
      inputMode="tel"
      autoComplete={autoComplete}
      value={display}
      onChange={handleChange}
      onBlur={handleBlur}
      onPaste={handlePaste}
      disabled={disabled}
      placeholder={placeholder}
      className={className}
      aria-invalid={ariaInvalid}
      aria-describedby={ariaDescribedby}
      {...rest}
    />
  );
}
