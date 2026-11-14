"use client";

import { useEffect, useState } from "react";
import { fetchSiteConfig, type SiteConfig } from "@/lib/site-config";
import ComingSoonPage from "./ComingSoonPage";

interface SiteModeGateProps {
  children: React.ReactNode;
}

export function SiteModeGate({ children }: SiteModeGateProps) {
  // Default to null (unknown) — we optimistically render children until we know
  // the mode is "coming_soon". This prevents the nav-link blank-flash caused by
  // returning null while the fetch is in flight, which unmounted the entire layout
  // subtree (Header + main + Footer) on every hydration and client navigation.
  const [config, setConfig] = useState<SiteConfig | null>(null);

  useEffect(() => {
    fetchSiteConfig().then(setConfig);
  }, []);

  // Only gate when the fetch has resolved AND confirmed coming_soon.
  // While loading (config === null) or when live: render children immediately.
  // This is safe because the default/fallback is always "live".
  if (config?.mode === "coming_soon") {
    return <ComingSoonPage message={config.message} />;
  }

  return <>{children}</>;
}
