"use client";

import { useState } from "react";
import { Turnstile } from "@marsidev/react-turnstile";

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

// Requires 2+ char TLD — catches me@me.t which browser type="email" allows
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function validateHero(name: string, email: string): string | null {
  if (!name.trim()) return "Please enter your name.";
  if (!email.trim()) return "Please enter your email address.";
  if (!EMAIL_REGEX.test(email.trim()))
    return "Please enter a valid email address.";
  return null;
}

const TURNSTILE_SITE_KEY =
  process.env.NEXT_PUBLIC_CLOUDFLARE_TURNSTILE_SITE_KEY ??
  "1x00000000000000000000AA";

export default function HeroCharterForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [honeypot, setHoneypot] = useState("");
  const [status, setStatus] = useState<
    "idle" | "submitting" | "success" | "error"
  >("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (honeypot) return; // bot

    const validationError = validateHero(name, email);
    if (validationError) {
      setErrorMsg(validationError);
      setStatus("error");
      return;
    }

    setStatus("submitting");
    setErrorMsg("");

    const trimmedName = name.trim();
    const trimmedEmail = email.trim();

    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/v1/marketing/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: trimmedName,
          email: trimmedEmail,
          trade: "other",
          company_size: "solo",
          source: "homepage_hero",
          cf_turnstile_response: turnstileToken ?? "",
          honeypot,
        }),
      });

      if (res.ok || res.status === 200) {
        setStatus("success");
      } else {
        const data = await res.json().catch(() => ({}));
        const detail = data?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((err: { msg: string }) => err.msg).join(", ")
              : "Something went wrong. Please try again.";
        setErrorMsg(msg);
        setStatus("error");
      }
    } catch {
      setErrorMsg("Unable to connect. Please try again.");
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div
        className="rounded-xl p-6 text-center"
        style={{
          background: "var(--white-15)",
          border: "var(--border-white-20)",
        }}
        role="status"
        aria-live="polite"
      >
        <p className="text-xl font-bold mb-1" style={{ color: "var(--white)" }}>
          🎉 You{"'"}re on the list!
        </p>
        <p className="text-sm" style={{ color: "var(--white-8)" }}>
          We{"'"}ll email you when Charter opens.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="Charter signup"
      className="flex flex-col gap-3"
    >
      {/* Honeypot — visually hidden, NOT display:none */}
      <div className="honeypot-field" aria-hidden="true">
        <label htmlFor="hero-website">Website</label>
        <input
          id="hero-website"
          name="website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          value={honeypot}
          onChange={(e) => setHoneypot(e.target.value)}
        />
      </div>

      {/* Name (required) — full-width row above email+button */}
      <div>
        <label htmlFor="hero-name" className="sr-only">
          Your name
        </label>
        <input
          id="hero-name"
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          className="w-full px-4 py-3 rounded-lg text-base"
          style={{
            background: "var(--white-95)",
            border: "none",
            color: "var(--neutral-900)",
            outline: "none",
          }}
          autoComplete="name"
        />
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <label htmlFor="hero-email" className="sr-only">
          Enter your email
        </label>
        <input
          id="hero-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Enter your email"
          className="flex-1 px-4 py-3 rounded-lg text-base"
          style={{
            background: "var(--white-95)",
            border: "none",
            color: "var(--neutral-900)",
            outline: "none",
          }}
          autoComplete="email"
        />
        <button
          type="submit"
          className="btn-white whitespace-nowrap"
          disabled={status === "submitting" || !turnstileToken}
          aria-busy={status === "submitting"}
        >
          {status === "submitting"
            ? "Joining..."
            : "Be one of the first twelve"}
        </button>
      </div>

      {/* Turnstile — flexible widget (auto-executes on mount; visible on challenge) */}
      <div>
        <Turnstile
          siteKey={TURNSTILE_SITE_KEY}
          onSuccess={(token) => setTurnstileToken(token)}
          onError={() => setTurnstileToken(null)}
          onExpire={() => setTurnstileToken(null)}
          options={{ size: "flexible" }}
        />
      </div>

      {status === "error" && errorMsg && (
        <p
          className="text-sm rounded-lg px-3 py-2"
          style={{
            background: "var(--white-15)",
            color: "var(--white)",
            border: "var(--divider-thin) solid var(--white-30)",
          }}
          role="alert"
        >
          {errorMsg}
        </p>
      )}

      <p className="text-sm" style={{ color: "var(--white-6)" }}>
        90 days free · No credit card required
      </p>
    </form>
  );
}
