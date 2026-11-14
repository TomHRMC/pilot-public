/**
 * ProfileSettingsForm — FE-B12 / FE-UI-NAV-S1
 *
 * Location: apps/web/src/features/account-settings/components/ProfileSettingsForm.tsx
 *
 * Name, email, timezone fields save-on-blur (no save button).
 * Profile photo upload: S3 signed URL pattern (FE-UI-NAV-S1 addition).
 *
 * FE-UI-NAV-S1 additions:
 *   - 64px avatar preview (photo or initials)
 *   - "Change" button (hidden file input) + "Remove" button
 *   - AvatarCropModal appears after file selection
 *   - useAvatarUpload / useAvatarDelete hooks
 */

"use client";

import React, { useState } from "react";
import { useAuth } from "@pilot/ui/auth";
import { PhoneInput } from "@pilot/ui/phone-input";
import { AvatarCropModal } from "@/components/AvatarCropModal";
import {
  useAvatarUpload,
  useAvatarDelete,
} from "@/features/settings/hooks/useAvatarUpload";
import { useUpdateProfile } from "../hooks/useUpdateProfile";

const TIMEZONE_OPTIONS = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "America/Anchorage",
  "Pacific/Honolulu",
  "America/Puerto_Rico",
];

function getInitials(displayName?: string, email?: string): string {
  const name = displayName?.trim();
  if (name) {
    const parts = name.split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }
  return (email?.[0] ?? "?").toUpperCase();
}

interface ProfileFormInnerProps {
  initialFirstName: string;
  initialLastName: string;
  initialPhone: string | null;
  initialTimezone: string;
  email: string;
  isPending: boolean;
  updateError: Error | null | undefined;
  onSave: (field: string, value: string | null) => Promise<void>;
}

function ProfileFormInner({
  initialFirstName,
  initialLastName,
  initialPhone,
  initialTimezone,
  email,
  isPending,
  updateError,
  onSave,
}: ProfileFormInnerProps) {
  const { user } = useAuth();
  const [firstName, setFirstName] = useState(initialFirstName);
  const [lastName, setLastName] = useState(initialLastName);
  const [phone, setPhone] = useState<string | null>(initialPhone);
  const [timezone, setTimezone] = useState(initialTimezone);
  const [saveStatus, setSaveStatus] = useState<
    Record<string, "saved" | "error" | null>
  >({});
  // FE-UI-NAV-S1: crop modal state
  const [cropFile, setCropFile] = useState<File | null>(null);
  const avatarUpload = useAvatarUpload();
  const avatarDelete = useAvatarDelete();

  const initials = getInitials(user?.displayName, user?.email);

  const handleBlurSave = async (field: string, value: string | null) => {
    try {
      await onSave(field, value);
      setSaveStatus((prev) => ({ ...prev, [field]: "saved" }));
      setTimeout(
        () => setSaveStatus((prev) => ({ ...prev, [field]: null })),
        2000,
      );
    } catch {
      setSaveStatus((prev) => ({ ...prev, [field]: "error" }));
    }
  };

  return (
    <>
      <form
        className="flex flex-col gap-5 max-w-md"
        data-testid="profile-settings-form"
      >
        {updateError && (
          <div
            role="alert"
            className="rounded-md bg-fault-50 border border-fault-200 p-3 text-sm text-fault-700"
          >
            {updateError instanceof Error
              ? updateError.message
              : "Failed to save."}
          </div>
        )}

        {/* Avatar upload control — FE-UI-NAV-S1 */}
        <div className="flex items-start gap-4 mb-2">
          {/* 64px avatar preview */}
          <div className="w-16 h-16 rounded-full overflow-hidden ring-2 ring-neutral-200 shrink-0 bg-brand-600 flex items-center justify-center">
            {user?.profile_photo_url ? (
              // eslint-disable-next-line @next/next/no-img-element -- signed S3 URL; next/image requires domain allowlist config
              <img
                src={user.profile_photo_url}
                alt="Profile photo"
                className="w-full h-full object-cover"
              />
            ) : (
              <span className="text-lg font-semibold text-white">
                {initials}
              </span>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex gap-2 flex-wrap">
              {/* Hidden file input wrapped in <label> */}
              <label className="border border-neutral-300 text-neutral-700 rounded-md px-3 py-1.5 text-sm hover:bg-neutral-50 cursor-pointer transition-colors">
                Change
                <input
                  type="file"
                  accept="image/jpeg,image/png"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      if (file.size > 2 * 1024 * 1024) {
                        // 2MB limit
                        alert("File too large. Max 2MB.");
                        return;
                      }
                      setCropFile(file);
                      // Reset input so same file can be re-selected
                      e.target.value = "";
                    }
                  }}
                />
              </label>
              {user?.profile_photo_url && (
                <button
                  type="button"
                  onClick={() => avatarDelete.mutate()}
                  disabled={avatarDelete.isPending}
                  className="text-sm text-fault-600 hover:text-fault-700 hover:underline disabled:opacity-50"
                >
                  {avatarDelete.isPending ? "Removing…" : "Remove"}
                </button>
              )}
            </div>
            <p className="text-xs text-neutral-500">JPG or PNG, max 2MB</p>
            {avatarUpload.isError && (
              <p className="text-xs text-fault-600">
                Upload failed. Please try again.
              </p>
            )}
            {avatarUpload.isPending && (
              <p className="text-xs text-neutral-500">Uploading photo…</p>
            )}
          </div>
        </div>

        {/* First name */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="first-name"
            className="text-sm font-medium text-neutral-700"
          >
            First name
          </label>
          <div className="flex items-center gap-2">
            <input
              id="first-name"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              onBlur={() => handleBlurSave("first_name", firstName)}
              disabled={isPending}
              className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600 disabled:opacity-50"
              data-testid="first-name-input"
            />
            {saveStatus["first_name"] === "saved" && (
              <span className="text-xs text-margin-600">Saved</span>
            )}
          </div>
        </div>

        {/* Last name */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="last-name"
            className="text-sm font-medium text-neutral-700"
          >
            Last name
          </label>
          <div className="flex items-center gap-2">
            <input
              id="last-name"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              onBlur={() => handleBlurSave("last_name", lastName)}
              disabled={isPending}
              className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600 disabled:opacity-50"
              data-testid="last-name-input"
            />
            {saveStatus["last_name"] === "saved" && (
              <span className="text-xs text-margin-600">Saved</span>
            )}
          </div>
        </div>

        {/* Email — read-only */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="email"
            className="text-sm font-medium text-neutral-700"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            readOnly
            className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-500 cursor-not-allowed"
            aria-describedby="email-hint"
          />
          <p id="email-hint" className="text-xs text-neutral-400">
            Contact support to change your email address.
          </p>
        </div>

        {/* Phone */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="phone"
            className="text-sm font-medium text-neutral-700"
          >
            Phone number
          </label>
          <div className="flex items-center gap-2">
            <PhoneInput
              id="phone"
              value={phone ?? ""}
              onChange={(e164) => setPhone(e164)}
              onBlur={() => handleBlurSave("phone", phone)}
              disabled={isPending}
              className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600 disabled:opacity-50"
              data-testid="phone-input"
            />
            {saveStatus["phone"] === "saved" && (
              <span className="text-xs text-margin-600">Saved</span>
            )}
          </div>
        </div>

        {/* Timezone */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="timezone"
            className="text-sm font-medium text-neutral-700"
          >
            Timezone
          </label>
          <div className="flex items-center gap-2">
            <select
              id="timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              onBlur={() => handleBlurSave("timezone", timezone)}
              disabled={isPending}
              className="flex-1 rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600 disabled:opacity-50"
              data-testid="timezone-select"
            >
              {TIMEZONE_OPTIONS.map((tz) => (
                <option key={tz} value={tz}>
                  {tz.replace(/_/g, " ")}
                </option>
              ))}
            </select>
            {saveStatus["timezone"] === "saved" && (
              <span className="text-xs text-margin-600">Saved</span>
            )}
          </div>
        </div>
      </form>

      {/* Crop modal — rendered outside the <form> to avoid nesting issues */}
      {cropFile && (
        <AvatarCropModal
          imageFile={cropFile}
          onSave={(blob) => {
            setCropFile(null);
            avatarUpload.mutate(blob);
          }}
          onCancel={() => setCropFile(null)}
        />
      )}
    </>
  );
}

export function ProfileSettingsForm() {
  const { profile, isLoading, updateProfile, isPending, updateError } =
    useUpdateProfile();

  if (isLoading || !profile) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin h-5 w-5 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  return (
    // key=user_id ensures the inner form remounts with correct initial state when profile loads
    <ProfileFormInner
      key={profile.user_id}
      initialFirstName={profile.first_name}
      initialLastName={profile.last_name}
      initialPhone={profile.phone ?? ""}
      initialTimezone={profile.timezone}
      email={profile.email}
      isPending={isPending}
      updateError={updateError}
      onSave={async (field, value) => {
        await updateProfile({ [field]: value });
      }}
    />
  );
}
