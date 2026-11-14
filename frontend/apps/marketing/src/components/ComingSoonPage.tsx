/**
 * ComingSoonPage — Full-page placeholder rendered by SiteModeGate when
 * site-config.json returns { "mode": "coming_soon" }.
 *
 * Design decisions:
 *   - Single screen, no scroll. Fits 375 px (iPhone SE) to 1440 px.
 *   - hero-gradient background (135 ° brand-600 → brand-900) so the page
 *     feels like the top of the live marketing site — not a stripped-down fallback.
 *   - btn-white CTA (white pill on blue) gives maximum contrast and re-uses the
 *     same token used in the homepage metrics-bar CTA.
 *   - No Header, Footer nav, forms, or links to other marketing pages.
 *   - All colour/shadow/typography values are CSS tokens from globals.css only.
 */

interface ComingSoonPageProps {
  /** Optional override message from site-config.json. Falls back to default. */
  message?: string;
}

const DEFAULT_MESSAGE =
  "We're getting ready. Sign up to be first in line when we launch.";

export default function ComingSoonPage({ message }: ComingSoonPageProps) {
  return (
    <main
      className="hero-gradient flex flex-col"
      style={{ minHeight: "100vh" }}
      aria-labelledby="cs-heading"
    >
      {/* ── Content area — vertically centred, flex-1 absorbs remaining height ── */}
      <div
        className="flex-1 flex items-center justify-center"
        style={{ padding: "clamp(2rem, 6vw, 4rem) 1rem" }}
      >
        <div style={{ width: "100%", maxWidth: "34rem", textAlign: "center" }}>
          {/* ── Logo block ── */}
          <div
            className="flex items-center justify-center gap-3"
            style={{ marginBottom: "2rem" }}
          >
            {/* Brand icon — same SVG as Header, adjusted fill for blue bg */}
            <svg
              width="40"
              height="40"
              viewBox="0 0 28 28"
              fill="none"
              aria-hidden="true"
            >
              <rect width="28" height="28" rx="6" fill="var(--white-15)" />
              <path
                d="M8 14l4 4 8-8"
                stroke="white"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>

            {/* Wordmark */}
            <span
              style={{
                fontSize: "1.25rem",
                fontWeight: 700,
                color: "var(--white)",
                lineHeight: 1,
              }}
            >
              Pilot for Trades
            </span>
          </div>

          {/* ── Eyebrow badge ── */}
          <div style={{ marginBottom: "1.5rem" }}>
            <span
              className="text-caption-lg rounded-full"
              style={{
                display: "inline-block",
                fontWeight: 500,
                padding: "0.375rem 1rem",
                background: "var(--white-15)",
                color: "var(--white)",
                border: "var(--border-white-20)",
              }}
            >
              AI-Powered Tools for Electrical Contractors
            </span>
          </div>

          {/* ── H1 — product name (SEO anchor for the page) ── */}
          <h1
            id="cs-heading"
            className="text-section-title"
            style={{
              color: "var(--white)",
              marginBottom: "1rem",
            }}
          >
            Pilot for Trades
          </h1>

          {/* ── Value proposition — ≤ 20 words ── */}
          <p
            className="text-section-subtitle"
            style={{
              color: "var(--white-85)",
              marginBottom: "1.5rem",
            }}
          >
            Voice-controlled quoting, dispatch, and job tracking — built for the
            field.
          </p>

          {/* ── Optional/default message ── */}
          <p
            className="text-body-lg"
            style={{
              color: "var(--white-7)",
              marginBottom: "2.5rem",
            }}
          >
            {message ?? DEFAULT_MESSAGE}
          </p>

          {/* ── Primary CTA — mailto, no form, no API ── */}
          <a
            href="mailto:sales@pilotfortrades.com"
            className="btn-white"
            style={{ boxShadow: "var(--shadow-xl)" }}
          >
            Be one of the first twelve
          </a>
        </div>
      </div>

      {/* ── Minimal legal footer ── */}
      <footer
        style={{
          textAlign: "center",
          padding: "1.25rem 1rem",
          borderTop: "var(--border-white-12)",
        }}
        aria-label="Legal"
      >
        <p
          className="text-caption-lg"
          style={{ color: "var(--white-55)", marginBottom: "0.25rem" }}
        >
          © 2026 Example Holdings, LLC. All rights
          reserved.
        </p>
        <a
          href="mailto:legal@pilotfortrades.com"
          className="text-caption-lg"
          style={{
            color: "var(--white-55)",
            textDecoration: "none",
          }}
        >
          legal@pilotfortrades.com
        </a>
      </footer>
    </main>
  );
}
