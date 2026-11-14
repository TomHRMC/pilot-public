export type SiteMode = "live" | "coming_soon";

export interface SiteConfig {
  mode: SiteMode;
  message?: string;
}

const DEFAULT_CONFIG: SiteConfig = { mode: "live" };

export async function fetchSiteConfig(): Promise<SiteConfig> {
  try {
    const res = await fetch("/site-config.json", {
      cache: "no-store",
    });
    if (!res.ok) return DEFAULT_CONFIG;
    const data = await res.json();
    // Validate that mode is a known value — default to 'live' if invalid
    if (data.mode !== "live" && data.mode !== "coming_soon") {
      return DEFAULT_CONFIG;
    }
    return data as SiteConfig;
  } catch {
    // Network error, parse error, or missing file → fail open (show live site)
    return DEFAULT_CONFIG;
  }
}
