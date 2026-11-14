"use client";

/**
 * ProfileDropdown — header profile avatar + dropdown menu
 *
 * Location: apps/web/src/components/ProfileDropdown.tsx
 *
 * UI-FIX-2E: Avatar circle showing initials, dropdown with account links
 * and Sign Out. Outside-click and Escape dismiss.
 *
 * PilotUser shape: { displayName: string; email: string }
 * Initials: first two letters of displayName, or first letter of email.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@pilot/ui/auth";
import { useLogout } from "@/hooks/useLogout";
import type { PilotUser } from "@pilot/ui/auth";

function getInitials(user: PilotUser): string {
  const name = user.displayName?.trim();
  if (name) {
    const parts = name.split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }
  return (user.email?.[0] ?? "?").toUpperCase();
}

// FE-UI-NAV-S1: 3 personal items only (Subscription + Payment Method removed; Notifications added)
const DROPDOWN_ITEMS = [
  { label: "My Profile", href: "/settings/my-account/profile" },
  { label: "Security", href: "/settings/my-account/security" },
  { label: "Notifications", href: "/settings/notifications/preferences" },
] as const;

export function ProfileDropdown() {
  const { user } = useAuth();
  const { logout } = useLogout();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setIsOpen(false), []);

  // Outside-click dismiss
  useEffect(() => {
    if (!isOpen) return;

    function handleMouseDown(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        close();
      }
    }

    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [isOpen, close]);

  // Escape key dismiss
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        close();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, close]);

  const initials = user ? getInitials(user) : "?";

  return (
    <div ref={containerRef} className="relative">
      {/* Avatar button — FE-UI-NAV-S1: hover ring + conditional photo */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label="Open profile menu"
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 hover:ring-2 hover:ring-brand-300 hover:ring-offset-1 transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 overflow-hidden"
      >
        {user?.profile_photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element -- signed S3 URL; next/image requires domain allowlist config
          <img
            src={user.profile_photo_url}
            alt={user.displayName ?? "Profile"}
            className="w-full h-full rounded-full object-cover object-center"
            onError={(e) => {
              // Fallback to initials if image fails to load
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          initials
        )}
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div
          role="menu"
          aria-label="Profile menu"
          className="absolute top-full right-0 mt-1 min-w-48 bg-white border border-neutral-200 rounded-lg shadow-lg z-40 py-1 overflow-hidden"
        >
          {/* User info header */}
          {user && (
            <div className="px-4 py-2 border-b border-neutral-100">
              <p className="text-xs font-semibold text-neutral-900 truncate">
                {user.displayName}
              </p>
              <p className="text-xs text-neutral-500 truncate">{user.email}</p>
            </div>
          )}

          {/* Nav items */}
          {DROPDOWN_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              role="menuitem"
              onClick={close}
              className="flex items-center px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 hover:text-neutral-900 transition-colors duration-100"
            >
              {item.label}
            </Link>
          ))}

          {/* Divider */}
          <div className="border-t border-neutral-100 my-1" />

          {/* Sign Out */}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              close();
              void logout();
            }}
            className="flex items-center w-full px-4 py-2 text-sm text-fault-600 font-medium hover:bg-fault-50 hover:text-fault-700 transition-colors duration-100"
          >
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
