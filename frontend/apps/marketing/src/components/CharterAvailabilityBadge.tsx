"use client";

import { useEffect, useState } from "react";

/**
 * CharterAvailabilityBadge — C-B13 Part B
 *
 * Client component that fetches GET /api/v1/public/charter-availability
 * and renders a scarcity / open / full badge below the /charter hero headline.
 *
 * Scarcity rule (GTM §6.8): numeric count shown only when remaining <= 8.
 * When remaining > 8, shows a non-numeric "Charter program is open" line.
 * When open == false, shows "Charter program is full."
 * Fails silently on loading or error (progressive enhancement).
 *
 * @see mkt-c-b13-design-spec.md (private design spec, not in the public snapshot) §2.1, §4.1
 */

interface CharterAvailability {
  open: boolean;
  remaining: number;
}

type BadgeState =
  | { status: "loading" }
  | { status: "scarcity"; remaining: number }
  | { status: "open" }
  | { status: "full" };

export default function CharterAvailabilityBadge() {
  const [state, setState] = useState<BadgeState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    fetch(`${backendUrl}/api/v1/public/charter-availability`, {
      signal: controller.signal,
      cache: "no-store",
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data: CharterAvailability | null) => {
        if (cancelled || !data) return;
        if (!data.open || data.remaining <= 0) {
          setState({ status: "full" });
        } else if (data.remaining <= 8) {
          setState({ status: "scarcity", remaining: data.remaining });
        } else {
          setState({ status: "open" });
        }
      })
      .catch(() => {
        // Fail silently — badge is progressive enhancement, not critical path.
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  // Loading and error states render nothing.
  if (state.status === "loading") {
    return null;
  }

  if (state.status === "scarcity") {
    return (
      <div
        className="mb-6"
        role="status"
        aria-live="polite"
        style={{ animation: "charter-badge-fade-in 200ms ease-out" }}
      >
        <span
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full font-semibold"
          style={{
            fontSize: "var(--text-caption-lg)",
            lineHeight: "var(--lh-caption-lg)",
            background: "var(--alert-50)",
            color: "var(--alert-600)",
            border: "var(--divider-thin) solid var(--alert-400)",
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M8 1.5L0.75 14h14.5L8 1.5z"
              stroke="var(--alert-600)"
              strokeWidth="1.5"
              strokeLinejoin="round"
              fill="none"
            />
            <path
              d="M8 6v3"
              stroke="var(--alert-600)"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <circle cx="8" cy="11.5" r="0.75" fill="var(--alert-600)" />
          </svg>
          Only {state.remaining} spots remaining
        </span>
      </div>
    );
  }

  if (state.status === "open") {
    return (
      <div
        className="mb-6"
        role="status"
        aria-live="polite"
        style={{ animation: "charter-badge-fade-in 200ms ease-out" }}
      >
        <span
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full font-semibold"
          style={{
            fontSize: "var(--text-caption-lg)",
            lineHeight: "var(--lh-caption-lg)",
            background: "var(--white-15)",
            color: "var(--white-85)",
            border: "var(--divider-thin) solid var(--white-3)",
          }}
        >
          Charter program is open
        </span>
      </div>
    );
  }

  // full
  return (
    <div
      className="mb-6"
      role="status"
      aria-live="polite"
      style={{ animation: "charter-badge-fade-in 200ms ease-out" }}
    >
      <span
        className="inline-flex items-center gap-2 px-4 py-2 rounded-full font-semibold"
        style={{
          fontSize: "var(--text-caption-lg)",
          lineHeight: "var(--lh-caption-lg)",
          background: "var(--white-15)",
          color: "var(--white-7)",
          border: "var(--divider-thin) solid var(--white-3)",
        }}
      >
        Charter program is full
      </span>
    </div>
  );
}
