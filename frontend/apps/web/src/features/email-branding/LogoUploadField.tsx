/**
 * LogoUploadField — FE-B14
 *
 * Location: apps/web/src/features/email-branding/LogoUploadField.tsx
 *
 * S3 presigned upload pattern (same as FE-B7 photo uploads):
 *   POST /logo-upload-url → {upload_url, s3_path} → PUT directly to S3 → PATCH branding
 *
 * Token: text-fault-600 for errors.
 * RULE 5: No Pilot tokens for tenant brand colors — this is for the logo asset only.
 */

"use client";

import React, { useRef, useState } from "react";
import { apiClient } from "@pilot/shared-api";
import type { LogoUploadState } from "./types";

const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];
const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

interface LogoUploadFieldProps {
  currentLogoUrl: string | null;
  onLogoCommitted: (s3Path: string) => void;
  onLogoRemoved: () => void;
}

export function LogoUploadField({
  currentLogoUrl,
  onLogoCommitted,
  onLogoRemoved,
}: LogoUploadFieldProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadState, setUploadState] = useState<LogoUploadState>({
    phase: "idle",
    error: null,
    previewUrl: currentLogoUrl,
  });

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Client-side pre-validation
    if (!ALLOWED_TYPES.includes(file.type)) {
      setUploadState((prev) => ({
        ...prev,
        error: "Upload a PNG, JPEG, WebP, or GIF image.",
        phase: "idle",
      }));
      return;
    }

    if (file.size > MAX_SIZE_BYTES) {
      setUploadState((prev) => ({
        ...prev,
        error: "Logo must be smaller than 5 MB.",
        phase: "idle",
      }));
      return;
    }

    // Show local preview immediately
    const localPreview = URL.createObjectURL(file);
    setUploadState({
      phase: "requesting-url",
      error: null,
      previewUrl: localPreview,
    });

    try {
      // Step 1: Request presigned upload URL (apiClient attaches JWT Bearer token)
      const { data } = await apiClient.post<{
        upload_url: string;
        s3_path: string;
      }>("/api/v1/settings/email-branding/logo-upload-url", {
        content_type: file.type,
        file_size_bytes: file.size,
      });

      const { upload_url, s3_path } = data;

      // Step 2: Upload directly to S3 via presigned URL
      setUploadState((prev) => ({ ...prev, phase: "uploading" }));
      const s3Res = await fetch(upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
      });

      if (!s3Res.ok) {
        throw new Error("Upload failed. Please try again.");
      }

      // Step 3: Commit to branding settings
      setUploadState((prev) => ({ ...prev, phase: "committing" }));
      onLogoCommitted(s3_path);

      setUploadState((prev) => ({ ...prev, phase: "success" }));
    } catch (err) {
      setUploadState((prev) => ({
        ...prev,
        phase: "error",
        error: err instanceof Error ? err.message : "Upload failed.",
        previewUrl: currentLogoUrl,
      }));
    }

    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const isUploading =
    uploadState.phase === "requesting-url" ||
    uploadState.phase === "uploading" ||
    uploadState.phase === "committing";

  return (
    <div className="flex flex-col gap-3" data-testid="logo-upload-field">
      <div className="flex items-center gap-4">
        {/* Logo preview */}
        <div className="h-16 w-40 rounded-lg border border-neutral-200 bg-neutral-50 flex items-center justify-center overflow-hidden">
          {uploadState.previewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={uploadState.previewUrl}
              alt="Logo preview"
              className="max-h-full max-w-full object-contain"
              data-testid="logo-preview"
            />
          ) : (
            <span className="text-xs text-neutral-400">No logo</span>
          )}
        </div>

        {/* Upload / Remove actions */}
        <div className="flex flex-col gap-2">
          <button
            type="button"
            disabled={isUploading}
            onClick={() => fileInputRef.current?.click()}
            className="rounded-lg border border-neutral-300 px-3 py-1.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
            data-testid="logo-upload-button"
          >
            {isUploading
              ? uploadState.phase === "uploading"
                ? "Uploading…"
                : "Processing…"
              : uploadState.previewUrl
                ? "Change logo"
                : "Upload logo"}
          </button>
          {uploadState.previewUrl && (
            <button
              type="button"
              disabled={isUploading}
              onClick={() => {
                setUploadState({
                  phase: "idle",
                  error: null,
                  previewUrl: null,
                });
                onLogoRemoved();
              }}
              className="text-xs text-fault-600 hover:underline disabled:opacity-50 text-left"
              data-testid="logo-remove-button"
            >
              Remove
            </button>
          )}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={ALLOWED_TYPES.join(",")}
        className="hidden"
        onChange={handleFileSelect}
        data-testid="logo-file-input"
      />

      {/* Helper text */}
      <p className="text-xs text-neutral-400">
        PNG, JPEG, WebP, or GIF · Max 5 MB · Recommended 400×100px
      </p>

      {/* Error */}
      {uploadState.error && (
        <p className="text-sm text-fault-600" data-testid="logo-upload-error">
          {uploadState.error}
        </p>
      )}
    </div>
  );
}
