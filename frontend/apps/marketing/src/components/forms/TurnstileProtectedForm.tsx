/**
 * TurnstileProtectedForm — shared security base for all marketing forms.
 *
 * §6.7 Shared Frontend Security Pattern:
 *   - Owns one @marsidev/react-turnstile instance per form mount
 *   - Owns the CSS-hidden honeypot field (NOT display:none — bots skip those)
 *   - Exposes { turnstileToken, honeypot, isReady } via useTurnstileProtection() hook
 *   - Disables the submit button until Turnstile resolves
 *
 * Usage:
 *   <TurnstileProtectedForm onSubmit={myHandler} ariaLabel="...">
 *     {({ isReady }) => (
 *       <>
 *         // form fields
 *         <button type="submit" disabled={!isReady}>Submit</button>
 *       </>
 *     )}
 *   </TurnstileProtectedForm>
 *
 * Child form components call useTurnstileProtection() to get
 * turnstileToken and honeypot to include in the POST body.
 */

"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useId,
  type ReactNode,
} from "react";
import { Turnstile } from "@marsidev/react-turnstile";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TURNSTILE_SITE_KEY =
  process.env.NEXT_PUBLIC_CLOUDFLARE_TURNSTILE_SITE_KEY ??
  "1x00000000000000000000AA"; // Cloudflare always-passes test key for local dev

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface TurnstileContextValue {
  /** Cloudflare Turnstile challenge token — null until resolved */
  turnstileToken: string | null;
  /** Honeypot field value — must remain empty for real users */
  honeypot: string;
  /** True once Turnstile has resolved a valid token */
  isReady: boolean;
}

const TurnstileContext = createContext<TurnstileContextValue>({
  turnstileToken: null,
  honeypot: "",
  isReady: false,
});

// ---------------------------------------------------------------------------
// Hook — consumed by child form components
// ---------------------------------------------------------------------------

/**
 * Returns the Turnstile token + honeypot value to inject into POST bodies.
 * Must be called inside a <TurnstileProtectedForm> subtree.
 */
export function useTurnstileProtection(): TurnstileContextValue {
  return useContext(TurnstileContext);
}

// ---------------------------------------------------------------------------
// Shared UI helpers — exported so all forms use consistent styling
// ---------------------------------------------------------------------------

/** Animated spinner for submitting state */
export function SubmitSpinner() {
  return (
    <svg
      className="animate-spin"
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="9" cy="9" r="7" stroke="var(--white-30)" strokeWidth="2" />
      <path
        d="M9 2a7 7 0 017 7"
        stroke="var(--white)"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Consistent error alert — same style across all forms */
export function FormErrorAlert({ message }: { message: string }) {
  return (
    <div
      className="rounded-lg px-4 py-3"
      style={{
        background: "var(--fault-50)",
        border: "var(--divider-thin) solid var(--fault-400)",
        color: "var(--fault-600)",
      }}
      role="alert"
      aria-live="assertive"
    >
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface TurnstileProtectedFormProps {
  /**
   * Render prop — receives { isReady } so children can disable the submit button.
   * Children call useTurnstileProtection() to get the token + honeypot for POST.
   */
  children: (ctx: { isReady: boolean }) => ReactNode;
  /** Passed directly to the underlying <form> element */
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  /** Accessible label for the form */
  ariaLabel?: string;
  /** Additional CSS class on the <form> element */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TurnstileProtectedForm({
  children,
  onSubmit,
  ariaLabel,
  className,
}: TurnstileProtectedFormProps) {
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [honeypot, setHoneypot] = useState("");

  // useId() is React 18 — stable, SSR-safe, no Math.random impurity
  const honeypotId = useId();

  const handleSuccess = useCallback((token: string) => {
    setTurnstileToken(token);
  }, []);

  const handleReset = useCallback(() => {
    setTurnstileToken(null);
  }, []);

  const isReady = turnstileToken !== null;

  return (
    <TurnstileContext.Provider value={{ turnstileToken, honeypot, isReady }}>
      <form
        onSubmit={onSubmit}
        noValidate
        aria-label={ariaLabel}
        className={className}
      >
        {/*
         * Honeypot — CSS-position hidden, NOT display:none.
         * Bots fill all visible fields; real users never see or interact with this.
         * The server rejects any submission where honeypot is non-empty.
         */}
        <div className="honeypot-field" aria-hidden="true">
          <label htmlFor={honeypotId}>Website</label>
          <input
            id={honeypotId}
            name="website"
            type="text"
            tabIndex={-1}
            autoComplete="off"
            value={honeypot}
            onChange={(e) => setHoneypot(e.target.value)}
          />
        </div>

        {/* Form-specific fields + submit button via render prop */}
        {children({ isReady })}

        {/* Cloudflare Turnstile — managed invisible challenge widget */}
        <div className="mt-3">
          <Turnstile
            siteKey={TURNSTILE_SITE_KEY}
            onSuccess={handleSuccess}
            onError={handleReset}
            onExpire={handleReset}
            options={{ size: "flexible" }}
          />
        </div>
      </form>
    </TurnstileContext.Provider>
  );
}
