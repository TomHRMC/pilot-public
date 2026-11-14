"use client";

/**
 * AvatarCropModal — FE-UI-NAV-S1
 *
 * Location: apps/web/src/components/AvatarCropModal.tsx
 *
 * Circular crop modal for profile photo upload.
 * Uses canvas center-crop to produce a 256×256 JPEG blob.
 *
 * Note: react-easy-crop is not installed. This implements a simplified
 * center-crop without a library (per Rule 8 — no new npm packages without
 * Tom's approval). The crop area is a circular preview of the uploaded image.
 *
 * Design spec §21.4: 240px circular preview, Save/Cancel buttons.
 */

import { useCallback } from "react";

interface AvatarCropModalProps {
  imageFile: File;
  onSave: (croppedBlob: Blob) => void;
  onCancel: () => void;
}

export function AvatarCropModal({
  imageFile,
  onSave,
  onCancel,
}: AvatarCropModalProps) {
  const imageUrl = URL.createObjectURL(imageFile);

  const handleSave = useCallback(() => {
    // Simplified center-crop: renders image to 256×256 canvas as JPEG at 90% quality
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 256;
      canvas.height = 256;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      // Center-crop square from the source image
      const size = Math.min(img.width, img.height);
      const x = (img.width - size) / 2;
      const y = (img.height - size) / 2;
      ctx.drawImage(img, x, y, size, size, 0, 0, 256, 256);

      canvas.toBlob(
        (blob) => {
          if (blob) onSave(blob);
          URL.revokeObjectURL(imageUrl);
        },
        "image/jpeg",
        0.9,
      );
    };
    img.src = imageUrl;
  }, [onSave, imageUrl]);

  return (
    <div
      className="fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center pt-16"
      role="dialog"
      aria-modal="true"
      aria-label="Crop photo"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-sm w-full mx-4 p-6">
        <h3 className="text-base font-medium text-neutral-900 mb-4">
          Crop photo
        </h3>

        {/* Circular 240px preview */}
        <div className="w-60 h-60 mx-auto rounded-full overflow-hidden border-2 border-neutral-200 mb-6">
          {/* eslint-disable-next-line @next/next/no-img-element -- blob URL from local file; next/image does not support blob: scheme */}
          <img
            src={imageUrl}
            alt="Photo preview"
            className="w-full h-full object-cover"
          />
        </div>

        <p className="text-xs text-neutral-400 text-center mb-4">
          Your photo will be cropped to a square.
        </p>

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            Save photo
          </button>
        </div>
      </div>
    </div>
  );
}
