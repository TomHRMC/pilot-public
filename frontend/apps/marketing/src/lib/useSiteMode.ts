/**
 * useSiteMode.ts — MKT-B11-C2
 *
 * Single source of truth for the site operating mode.
 * Reads from GET /api/v1/subscription-tiers/test (unauthenticated).
 *
 * Mode resolution:
 *   - tier_name === 'charter' active → Charter Mode
 *   - tier_name === 'starter' or 'teams' active → General Release Mode
 *   - On any fetch failure → fail open to Charter Mode (safer default)
 *
 * Rules:
 *   - Uses cache: 'no-store' — mode must reflect live DB, not a stale build cache
 *   - Uses /test endpoint — marketing site has no user auth
 *   - Never hardcode the mode or read from .env
 */

export type SiteMode = "charter" | "general";

export interface SiteModeResult {
  mode: SiteMode;
  isCharterMode: boolean;
  isGeneralRelease: boolean;
}

interface SubscriptionTier {
  tier_id: string;
  tier_name: string;
  display_label: string;
  monthly_price_cents: number;
  is_trial: boolean;
  trial_duration_days: number;
  schedule_lanes: number;
  display_order: number;
}

interface SubscriptionTiersResponse {
  tiers: SubscriptionTier[];
}

const CHARTER_MODE: SiteModeResult = {
  mode: "charter",
  isCharterMode: true,
  isGeneralRelease: false,
};

/**
 * getSiteMode — server-side fetch (for use in server components and generateMetadata).
 * Call this at the top of any page or layout server component that needs mode-aware rendering.
 */
export async function getSiteMode(): Promise<SiteModeResult> {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(
      `${backendUrl}/api/v1/subscription-tiers/test`,
      { cache: "no-store" }, // must reflect live DB — not build-time cache
    );
    if (!res.ok) return CHARTER_MODE;

    const data: SubscriptionTiersResponse = await res.json();
    const tiers: SubscriptionTier[] = data.tiers ?? [];

    const hasCharter = tiers.some((t) => t.tier_name === "charter");
    const hasGeneral = tiers.some(
      (t) => t.tier_name === "starter" || t.tier_name === "teams",
    );

    // General Release takes precedence if starter/teams tiers exist
    const mode: SiteMode = hasGeneral && !hasCharter ? "general" : "charter";

    return {
      mode,
      isCharterMode: mode === "charter",
      isGeneralRelease: mode === "general",
    };
  } catch {
    // Network error or parse failure → fail open to Charter mode.
    // Safer than accidentally showing General Release pricing during an outage.
    return CHARTER_MODE;
  }
}
