/**
 * BrandColorField — FE-B14
 *
 * Location: apps/web/src/features/email-branding/BrandColorField.tsx
 *
 * Free hex input + native color picker swatch.
 * RULE 5: This is the TENANT's brand color — NOT a Pilot token.
 *         A native <input type="color"> paired with a text hex input.
 *         No third-party library dependency.
 *
 * saveMode='blur': saves on blur (consistent with SettingControl pattern from FE-B11).
 */

"use client";

import React, { useState } from "react";

const HEX_PATTERN = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;

interface BrandColorFieldProps {
  value: string; // hex string e.g. '#E05A2B'
  onSave: (newColor: string) => void; // called on blur when valid
  label?: string;
}

export function BrandColorField({
  value,
  onSave,
  label = "Brand color",
}: BrandColorFieldProps) {
  const [draft, setDraft] = useState(value);
  const [error, setError] = useState<string | null>(null);

  function isValid(hex: string) {
    return HEX_PATTERN.test(hex);
  }

  function handleTextChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value;
    setDraft(raw);
    // Clear error while typing
    if (error) setError(null);
  }

  function handleColorPickerChange(e: React.ChangeEvent<HTMLInputElement>) {
    // Native color picker always returns #RRGGBB format
    const hex = e.target.value;
    setDraft(hex);
    setError(null);
  }

  function handleBlur() {
    if (!isValid(draft)) {
      setError("Enter a valid hex color (e.g. #E05A2B)");
      setDraft(value); // reset to last valid
      return;
    }
    setError(null);
    if (draft !== value) {
      onSave(draft);
    }
  }

  const swatchColor = isValid(draft) ? draft : value;

  return (
    <div className="flex flex-col gap-2" data-testid="brand-color-field">
      <label className="text-sm font-medium text-neutral-700">{label}</label>
      <div className="flex items-center gap-3">
        {/* Native color picker */}
        <div className="relative">
          <input
            type="color"
            value={swatchColor}
            onChange={handleColorPickerChange}
            onBlur={handleBlur}
            className="h-10 w-10 cursor-pointer rounded-lg border border-neutral-300 p-0.5"
            style={{ backgroundColor: swatchColor }}
            data-testid="color-picker-native"
            aria-label="Color picker"
          />
        </div>

        {/* Hex text input */}
        <input
          type="text"
          value={draft}
          onChange={handleTextChange}
          onBlur={handleBlur}
          maxLength={7}
          placeholder="#RRGGBB"
          className="w-28 rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono text-neutral-800 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
          data-testid="hex-input"
          aria-label="Hex color value"
        />

        {/* Live swatch preview */}
        <div
          className="h-9 w-9 rounded-lg border border-neutral-200 shadow-inner"
          style={{ backgroundColor: swatchColor }}
          data-testid="color-swatch"
          aria-hidden="true"
        />
      </div>

      {error && (
        <p className="text-sm text-fault-600" data-testid="color-error">
          {error}
        </p>
      )}

      <p className="text-xs text-neutral-400">
        This color is applied to your email headers and CTA buttons.
      </p>
    </div>
  );
}
